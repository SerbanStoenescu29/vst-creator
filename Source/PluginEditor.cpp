#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& p)
    : juce::AudioProcessorEditor(&p), processor(p)
{
    delayTimeSlider.setSliderStyle(juce::Slider::Rotary);
    delayTimeSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    addAndMakeVisible(delayTimeSlider);
    delayTimeLabel.setText("Delay Time (ms)", juce::dontSendNotification);
    delayTimeLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(delayTimeLabel);
    delayTimeAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "delayTime", delayTimeSlider);
    
    feedbackSlider.setSliderStyle(juce::Slider::Rotary);
    feedbackSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    addAndMakeVisible(feedbackSlider);
    feedbackLabel.setText("Repeats (%)", juce::dontSendNotification);
    feedbackLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(feedbackLabel);
    feedbackAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "feedback", feedbackSlider);
    
    mixSlider.setSliderStyle(juce::Slider::Rotary);
    mixSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    addAndMakeVisible(mixSlider);
    mixLabel.setText("Wet/Dry Mix (%)", juce::dontSendNotification);
    mixLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(mixLabel);
    mixAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "mix", mixSlider);
    
    setSize(500, 250);
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
}

void VstAiDemoAudioProcessorEditor::resized()
{
    int knobSize = 100;
    int knobSpacing = 150;
    int startX = 25;
    int knobY = 50;
    int labelY = 160;
    
    delayTimeSlider.setBounds(startX, knobY, knobSize, knobSize);
    delayTimeLabel.setBounds(startX, labelY, knobSize, 30);
    
    feedbackSlider.setBounds(startX + knobSpacing, knobY, knobSize, knobSize);
    feedbackLabel.setBounds(startX + knobSpacing, labelY, knobSize, 30);
    
    mixSlider.setBounds(startX + 2 * knobSpacing, knobY, knobSize, knobSize);
    mixLabel.setBounds(startX + 2 * knobSpacing, labelY, knobSize, 30);
}
