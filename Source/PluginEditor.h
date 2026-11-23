#pragma once

#include <JuceHeader.h>
#include "PluginProcessor.h"

class VstAiDemoAudioProcessorEditor final : public juce::AudioProcessorEditor
{
public:
    explicit VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor&);
    ~VstAiDemoAudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    juce::Label titleLabel;
    juce::Label mixLabel;
    juce::Label decayLabel;
    
    juce::Slider mixSlider;
    juce::Slider decaySlider;
    
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> mixAttachment;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> decayAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VstAiDemoAudioProcessorEditor)
};
