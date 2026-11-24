#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& p)
    : juce::AudioProcessorEditor(&p), processor(p)
{
    // Setup title label
    title.setText("VstAi Distortion", juce::dontSendNotification);
    title.setJustificationType(juce::Justification::centred);
    title.setFont(juce::Font(20.0f, juce::Font::bold));
    addAndMakeVisible(title);
    
    // Setup Drive slider
    driveSlider.setSliderStyle(juce::Slider::Rotary);
    driveSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    driveSlider.setRange(0.0, 1.0, 0.01);
    driveSlider.setValue(0.5);
    addAndMakeVisible(driveSlider);
    driveAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "drive", driveSlider);
    
    // Setup Drive label
    driveLabel.setText("Drive", juce::dontSendNotification);
    driveLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(driveLabel);
    
    // Setup Tone slider
    toneSlider.setSliderStyle(juce::Slider::Rotary);
    toneSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    toneSlider.setRange(0.0, 1.0, 0.01);
    toneSlider.setValue(0.5);
    addAndMakeVisible(toneSlider);
    toneAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "tone", toneSlider);
    
    // Setup Tone label
    toneLabel.setText("Tone", juce::dontSendNotification);
    toneLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(toneLabel);
    
    setSize(500, 350);
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
    
    // Draw some decorative elements
    g.setColour(juce::Colours::lightgrey);
    g.drawRect(getLocalBounds(), 2);
}

void VstAiDemoAudioProcessorEditor::resized()
{
    auto bounds = getLocalBounds();
    
    // Title at the top
    title.setBounds(bounds.removeFromTop(50));
    
    // Leave some margin
    bounds.reduce(20, 20);
    
    // Two columns for the sliders
    auto leftColumn = bounds.removeFromLeft(bounds.getWidth() / 2);
    auto rightColumn = bounds;
    
    // Drive slider and label
    auto driveArea = leftColumn;
    driveLabel.setBounds(driveArea.removeFromTop(30));
    driveSlider.setBounds(driveArea.removeFromTop(150).reduced(20, 0));
    
    // Tone slider and label
    auto toneArea = rightColumn;
    toneLabel.setBounds(toneArea.removeFromTop(30));
    toneSlider.setBounds(toneArea.removeFromTop(150).reduced(20, 0));
}