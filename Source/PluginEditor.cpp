#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& processor)
    : juce::AudioProcessorEditor(&processor), processorRef(processor)
{
    // Title Label
    titleLabel.setText("VstAiDemo Overdrive", juce::dontSendNotification);
    titleLabel.setJustificationType(juce::Justification::centred);
    titleLabel.setFont(juce::Font(24.0f, juce::Font::bold));
    titleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(titleLabel);

    // Drive Label
    driveLabel.setText("Drive", juce::dontSendNotification);
    driveLabel.setJustificationType(juce::Justification::centred);
    driveLabel.setFont(juce::Font(14.0f));
    driveLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    addAndMakeVisible(driveLabel);

    // Drive Slider
    driveSlider.setSliderStyle(juce::Slider::RotaryVerticalDrag);
    driveSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    driveSlider.setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::orange);
    driveSlider.setColour(juce::Slider::thumbColourId, juce::Colours::white);
    driveSlider.setColour(juce::Slider::textBoxTextColourId, juce::Colours::white);
    driveSlider.setColour(juce::Slider::textBoxBackgroundColourId, juce::Colours::darkgrey);
    addAndMakeVisible(driveSlider);
    driveAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processorRef.getAPVTS(), "drive", driveSlider);

    // Tone Label
    toneLabel.setText("Tone", juce::dontSendNotification);
    toneLabel.setJustificationType(juce::Justification::centred);
    toneLabel.setFont(juce::Font(14.0f));
    toneLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    addAndMakeVisible(toneLabel);

    // Tone Slider
    toneSlider.setSliderStyle(juce::Slider::RotaryVerticalDrag);
    toneSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    toneSlider.setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::cyan);
    toneSlider.setColour(juce::Slider::thumbColourId, juce::Colours::white);
    toneSlider.setColour(juce::Slider::textBoxTextColourId, juce::Colours::white);
    toneSlider.setColour(juce::Slider::textBoxBackgroundColourId, juce::Colours::darkgrey);
    addAndMakeVisible(toneSlider);
    toneAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processorRef.getAPVTS(), "tone", toneSlider);

    setSize(500, 300);
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
}

void VstAiDemoAudioProcessorEditor::resized()
{
    auto bounds = getLocalBounds();
    
    // Title at top
    titleLabel.setBounds(bounds.removeFromTop(50).reduced(10));
    
    // Remaining space for sliders
    auto sliderArea = bounds.reduced(20);
    
    // Drive control
    auto driveArea = sliderArea.removeFromLeft(sliderArea.getWidth() / 2).reduced(10);
    driveLabel.setBounds(driveArea.removeFromTop(30));
    driveSlider.setBounds(driveArea);
    
    // Tone control
    auto toneArea = sliderArea.reduced(10);
    toneLabel.setBounds(toneArea.removeFromTop(30));
    toneSlider.setBounds(toneArea);
}
